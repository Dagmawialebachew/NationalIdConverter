"""
apps/conversions/views.py
=========================
CBV views for the conversion flow. Completely locked down under strict 
authentication guidelines to maximize low-bandwidth edge-network performance.

Views:
    UploadView    — dual drag-and-drop file upload + runs conversion engine
    ResultView    — shows the converted landscape ID with download button
    DownloadView  — streams the output JPEG as a file download, then wipes bytes
    ImageView     — serves the JPEG preview bytes for the result page
    AdjustView    — accepts adjusted zone coordinates, re-runs the engine using
                    cached asset layers, returns new image (Field Adjustment Studio)
"""

import io
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, DetailView, View
from PIL import Image

# Core Mixins, Engine and Utilities
from core.mixins import QuotaMixin, PageTitleMixin, OwnerRequiredMixin
from core.engine import convert_bytes
from core.utils import read_uploaded_file, build_output_filename, file_download_response
from core.exceptions import ConversionFailedError, UnsupportedFileTypeError
from core.constants import FREE_DAILY_LIMIT

# App Specifics
from apps.conversions.forms import UploadForm
from apps.conversions.models import ConversionJob
from fayda_converter_v2 import extract_slices, render_layout_from_slices
from .signals import job_downloaded

logger = logging.getLogger(__name__)


@login_required
def get_current_credits_api(request):
    """
    Lightweight JSON endpoint providing immediate validation of live credit states.
    """
    try:
        quota = request.user.conversion_quota
        return JsonResponse({
            'success': True,
            'credits': "∞" if quota.is_unlimited else quota.remaining,
            'is_unlimited': quota.is_unlimited
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─── Cache Layer Management for Optimized Re-Rendering ────────────────────────

def cache_slices(job_id, slices):
    """
    Serializes and caches PIL image slices to Django's cache layer.
    Saves as PNG to preserve RGBA/Alpha channels (critical for portrait transparency).
    """
    serialized = {}
    for key, val in slices.items():
        if isinstance(val, Image.Image):
            buf = io.BytesIO()
            val.save(buf, format="PNG")
            serialized[key] = {
                "type": "image",
                "bytes": buf.getvalue()
            }
        else:
            serialized[key] = {
                "type": "str",
                "value": val
            }
    cache.set(f"slices_{job_id}", serialized, timeout=3600)


def get_cached_slices(job_id):
    """
    Retrieves and deserializes cached asset layers back into PIL Images.
    """
    serialized = cache.get(f"slices_{job_id}")
    if not serialized:
        return None
    
    slices = {}
    for key, data in serialized.items():
        if data["type"] == "image":
            slices[key] = Image.open(io.BytesIO(data["bytes"]))
        else:
            slices[key] = data["value"]
    return slices


# ─── Upload View ──────────────────────────────────────────────────────────────

class UploadView(LoginRequiredMixin, PageTitleMixin, QuotaMixin, FormView):
    """
    Enforces authentication BEFORE evaluating quota or checking inbound streams.
    Saves significant bandwidth on slow links by preventing file buffering for anon spam.
    """
    form_class = UploadForm
    template_name = "conversions/upload.html"
    page_title = "Convert Your Fayda ID"
    
    def handle_no_permission(self):
        messages.error(self.request, "Please sign in first to convert your ID.")
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        """
        Inspects incoming data logs while staying fully protected behind LoginRequiredMixin.
        """
        print("\n" + "=" * 60)
        print(" 🔍 RAW INBOUND FRONTEND PAYLOAD INSPECTOR 🔍 ")
        print("=" * 60)
        print("📥 POST Parameters:")
        for key, value in request.POST.items():
            if key == "custom_zones" and value:
                preview = value[:150] + "..." if len(value) > 150 else value
                print(f"  🔹 {key} (length: {len(value)}): {preview}")
            else:
                print(f"  🔹 {key}: {value}")

        print("\n📂 FILES Parameters:")
        for key, file_obj in request.FILES.items():
            print(f"  📂 {key}: {file_obj.name} ({file_obj.size} bytes | content_type={file_obj.content_type})")
        print("=" * 60 + "\n")

        logger.debug(
            "Frontend upload stream caught for authenticated user=%s. POST keys: %s | FILES keys: %s",
            request.user.email,
            list(request.POST.keys()),
            list(request.FILES.keys())
        )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        approach = cleaned_data["approach"]
        file_one = cleaned_data["file_one"]
        file_two = cleaned_data["file_two"]
        custom_zones = cleaned_data.get("custom_zones")

        user = self.request.user
        watermark = self._should_watermark(user)

        # 1. Initialize the conversion job record bound safely to the current user
        job = ConversionJob.objects.create(
            user=user,
            approach=approach,
            input_filename_one=file_one.name,
            input_bytes_one=read_uploaded_file(file_one),
            input_filename_two=file_two.name if file_two else "n/a",
            input_bytes_two=read_uploaded_file(file_two) if file_two else b"",
        )

        job.mark_processing()

        # 2. Scale custom coordinates from relative fractions to absolute pixels
        if custom_zones:
            try:
                if "front" in custom_zones and job.input_bytes_one:
                    with Image.open(io.BytesIO(job.input_bytes_one)) as img_front:
                        f_w, f_h = img_front.size

                    for zone_name, box in custom_zones["front"].items():
                        if any(isinstance(v, float) and v <= 1.0 for v in box.values()):
                            box["x1"] = int(box["x1"] * f_w)
                            box["x2"] = int(box["x2"] * f_w)
                            box["y1"] = int(box["y1"] * f_h)
                            box["y2"] = int(box["y2"] * f_h)

                if "back" in custom_zones and job.input_bytes_two:
                    with Image.open(io.BytesIO(job.input_bytes_two)) as img_back:
                        b_w, b_h = img_back.size

                    for zone_name, box in custom_zones["back"].items():
                        if any(isinstance(v, float) and v <= 1.0 for v in box.values()):
                            box["x1"] = int(box["x1"] * b_w)
                            box["x2"] = int(box["x2"] * b_w)
                            box["y1"] = int(box["y1"] * b_h)
                            box["y2"] = int(box["y2"] * b_h)

                logger.info("Successfully scaled relative zones to absolute pixels for job=%s", job.id)
            except Exception as scale_err:
                logger.error("Failed to dynamically scale custom zone targets: %s", scale_err)

        # 3. Pass the scaled coordinates to the core engine
        try:
            logger.info("UploadView: starting conversion engine for job=%s", job.id)

            output = convert_bytes(
                file_bytes_one=bytes(job.input_bytes_one),
                filename_one=job.input_filename_one,
                file_bytes_two=bytes(job.input_bytes_two),
                filename_two=job.input_filename_two,
                approach=job.approach,
                watermark=watermark,
                custom_zones=custom_zones,
            )

            job.mark_done(output_bytes=output, watermarked=watermark)
            
            # 4. Prime the cache layer with asset slices for instant adjustments
            try:
                slices = extract_slices(
                    file_bytes_one=bytes(job.input_bytes_one),
                    file_bytes_two=bytes(job.input_bytes_two),
                    filename_one=job.input_filename_one,
                    filename_two=job.input_filename_two,
                    custom_zones=custom_zones,
                )
                cache_slices(job.id, slices)
                logger.info("UploadView: Successfully primed asset slices cache for job=%s", job.id)
            except Exception as cache_err:
                logger.warning("UploadView: Asset slicing caching failed: %s", cache_err)
                
            logger.info("UploadView: success job=%s", job.id)
            return redirect(reverse("conversions:result", kwargs={"pk": job.id}))

        except (ConversionFailedError, UnsupportedFileTypeError) as exc:
            job.mark_failed(str(exc))
            messages.error(self.request, str(exc))
            return self._render_invalid_fallback(form, reason="engine_expected_failure")

        except Exception as exc:
            job.mark_failed("System error during processing.")
            logger.exception("UploadView: crash job=%s | custom_zones_payload=%s", job.id, custom_zones)
            messages.error(self.request, "An internal error occurred. Please try again.")
            return self._render_invalid_fallback(form, reason="engine_unexpected_crash")

    def form_invalid(self, form):
        logger.error("UploadView: Form Validation Failed | Errors: %s", form.errors.as_data())
        messages.error(self.request, "Please check your file selection and try again.")
        return super().form_invalid(form)

    def _render_invalid_fallback(self, form, reason):
        logger.warning("UploadView: Rendering form invalid fallback layout path due to: %s", reason)
        return super().form_invalid(form)

    def _should_watermark(self, user) -> bool:
        try:
            return user.conversion_quota.conversions_allowed == FREE_DAILY_LIMIT
        except Exception:
            return True


# ─── Result View ──────────────────────────────────────────────────────────────

class ResultView(LoginRequiredMixin, OwnerRequiredMixin, PageTitleMixin, DetailView):
    """
    Displays the output layout safely. Leverages OwnerRequiredMixin to block
    malicious or anonymous asset hunting via randomized UUID scanning.
    """
    model = ConversionJob
    template_name = "conversions/result.html"
    page_title = "Your Converted ID"
    context_object_name = "job"

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        return get_object_or_404(ConversionJob, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object
        context["download_url"] = reverse("conversions:download", kwargs={"pk": job.id})
        context["is_downloadable"] = job.is_downloadable
        context["is_failed"] = job.is_failed
        context["is_watermarked"] = job.watermarked
        return context


# ─── Download View ────────────────────────────────────────────────────────────

class DownloadView(LoginRequiredMixin, View):
    """
    Streams output JPEG arrays and clears heavy file system blobs right after execution.
    """
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        job = get_object_or_404(ConversionJob, pk=pk)

        # Explicit Object Ownership Check
        if job.user != request.user:
            raise Http404("Job not found.")

        if not job.is_downloadable or not job.output_bytes:
            messages.warning(request, "This file is no longer available.")
            return redirect("conversions:upload")

        filename = build_output_filename(str(job.id))
        response = file_download_response(
            content=bytes(job.output_bytes),
            filename=filename,
            content_type="image/jpeg",
        )

        # Broadcast download transaction to handle database adjustments atomically
        job_downloaded.send(
            sender=self.__class__, 
            job=job, 
            user=request.user
        )

        # Secure memory release sequence
        job.clear_output_bytes()
        job.clear_input_bytes()

        logger.info("DownloadView: file downloaded and database cleared for job=%s", job.id)
        return response


# ─── Image Preview View ───────────────────────────────────────────────────────

class ImageView(LoginRequiredMixin, View):
    """
    Serves the binary rendering layer directly into HTML preview components safely.
    """
    def get(self, request, pk):
        job = get_object_or_404(ConversionJob, pk=pk)

        if job.user != request.user:
            raise Http404("Not found.")

        if not job.output_bytes:
            raise Http404("Image not available.")

        return HttpResponse(job.output_bytes, content_type="image/jpeg")


# ─── Adjust View (Field Adjustment Studio) ────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class AdjustView(LoginRequiredMixin, View):
    """
    Processes interactive Canvas matrix transforms live via cached asset slices.
     Locked behind absolute auth pipelines to protect compute resources.
    """
    http_method_names = ["post"]
    _TW = 2360
    _TH = 667

    def post(self, request, pk, *args, **kwargs):
        job = get_object_or_404(ConversionJob, pk=pk)

        if job.user != request.user:
            raise Http404("Job not found.")

        if not job.is_downloadable:
            return JsonResponse(
                {"error": "This job is no longer available for adjustment. Please convert again."},
                status=400,
            )

        should_commit = request.GET.get("commit", "false") == "true"

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        output_zones = body.get("output_zones")
        if not output_zones or not isinstance(output_zones, dict):
            return JsonResponse({"error": "Missing or invalid 'output_zones' key in payload."}, status=400)

        if "front" not in output_zones and "back" not in output_zones:
            return JsonResponse({"error": "output_zones must contain at least a 'front' or 'back' key."}, status=400)

        validation_error = self._validate_output_zones(output_zones)
        if validation_error:
            return JsonResponse({"error": validation_error}, status=400)

        scaled_output_zones = self._scale_output_zones(output_zones)

        try:
            # 1. Fetch asset slices layer from fast cache map
            slices = get_cached_slices(job.id)
            
            # Cold cache fallback: Re-extract layers on demand
            if not slices:
                logger.info("AdjustView: Cache miss for job=%s. Re-extracting background layers.", job.id)
                slices = extract_slices(
                    file_bytes_one=bytes(job.input_bytes_one),
                    filename_one=job.input_filename_one,
                    file_bytes_two=bytes(job.input_bytes_two),
                    filename_two=job.input_filename_two,
                    custom_zones=None,
                )
                cache_slices(job.id, slices)

            # 2. Re-render composite layout with connection-aware compression parameters
            new_output = render_layout_from_slices(
                slices=slices,
                output_zones=scaled_output_zones,
                quality=60 if not should_commit else 95  # Light 60% quality for real-time streaming, 95% for ultimate final save
            )

        except (ConversionFailedError, UnsupportedFileTypeError) as exc:
            logger.warning("AdjustView: engine expected failure job=%s: %s", pk, exc)
            return JsonResponse({"error": str(exc)}, status=500)
        except Exception as exc:
            logger.exception("AdjustView: unexpected engine crash job=%s", pk)
            return JsonResponse(
                {"error": "Re-render failed due to an internal error. Please try again."},
                status=500,
            )

        if should_commit:
            job.output_bytes = new_output
            job.save(update_fields=["output_bytes"])
            logger.info("AdjustView: persisted finalized coordinates for job=%s (%d bytes)", pk, len(new_output))
            return JsonResponse({"ok": True})
        else:
            return HttpResponse(new_output, content_type="image/jpeg")

    @staticmethod
    def _validate_output_zones(output_zones: dict) -> str | None:
        for side in ("front", "back"):
            if side not in output_zones:
                continue
            if not isinstance(output_zones[side], dict):
                return f"'{side}' output_zones must be an object."

            for zone_name, box in output_zones[side].items():
                if not isinstance(box, dict):
                    return f"output_zone '{side}.{zone_name}' must be an object with x1/y1/x2/y2 keys."

                for key in ("x1", "y1", "x2", "y2"):
                    if key not in box:
                        return f"output_zone '{side}.{zone_name}' is missing required key '{key}'."
                    try:
                        val = float(box[key])
                    except (TypeError, ValueError):
                        return f"output_zone '{side}.{zone_name}.{key}' must be a number."
                    if not (0.0 <= val <= 1.0):
                        return (
                            f"output_zone '{side}.{zone_name}.{key}' value {val:.4f} is out of range [0, 1]. "
                            "All coordinates must be normalized canvas fractions."
                        )

                x1, y1 = float(box["x1"]), float(box["y1"])
                x2, y2 = float(box["x2"]), float(box["y2"])

                if x2 <= x1:
                    return f"output_zone '{side}.{zone_name}': x2 ({x2}) must be greater than x1 ({x1})."
                if y2 <= y1:
                    return f"output_zone '{side}.{zone_name}': y2 ({y2}) must be greater than y1 ({y1})."
        return None

    def _scale_output_zones(self, output_zones: dict) -> dict:
        scaled = {}
        for side in ("front", "back"):
            if side not in output_zones:
                continue
            scaled[side] = {}
            for zone_name, box in output_zones[side].items():
                scaled[side][zone_name] = {
                    "x1": int(float(box["x1"]) * self._TW),
                    "y1": int(float(box["y1"]) * self._TH),
                    "x2": int(float(box["x2"]) * self._TW),
                    "y2": int(float(box["y2"]) * self._TH),
                }
        return scaled