"""
apps/conversions/forms.py
=========================
Forms for the conversions app with defensive coordinate matrix parsing.
"""

import json
from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from core.utils import validate_upload
from core.exceptions import UnsupportedFileTypeError, FileTooLargeError, EmptyFileError
from core.constants import APPROACH_CHOICES, APPROACH_ONE, APPROACH_TWO

class UploadForm(forms.Form):
    approach = forms.ChoiceField(
        choices=APPROACH_CHOICES,
        required=False, 
        widget=forms.HiddenInput(attrs={"id": "id_approach"}),
    )
    custom_zones = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_custom_zones"}),
    )

    pdf_file = forms.FileField(required=False)
    front_image = forms.FileField(required=False)
    back_image = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False 
        self.helper.layout = Layout("approach", "custom_zones", "pdf_file", "front_image", "back_image")

    def clean(self):
        cleaned_data = super().clean()
        upload_mode = self.data.get('upload_mode', 'pdf')

        # Force the approach value if missing
        if not cleaned_data.get('approach'):
            cleaned_data['approach'] = APPROACH_ONE if upload_mode == 'pdf' else APPROACH_TWO

        # Map frontend inputs to 'file_one' / 'file_two'
        if upload_mode == 'pdf':
            file = cleaned_data.get('pdf_file')
            if not file:
                raise forms.ValidationError(_("Please select an e-Fayda PDF."))
            cleaned_data['file_one'] = self._validate_component(file)
            cleaned_data['file_two'] = None 
        else:
            f_img = cleaned_data.get('front_image')
            b_img = cleaned_data.get('back_image')
            if not f_img or not b_img:
                raise forms.ValidationError(_("Both front and back images are required."))
            cleaned_data['file_one'] = self._validate_component(f_img)
            cleaned_data['file_two'] = self._validate_component(b_img)
            
        return cleaned_data
    
    def clean_custom_zones(self):
        data = self.cleaned_data.get("custom_zones")
        if not data:
            return None
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                return None
                
            if "front" not in parsed and "back" not in parsed:
                return None

            # Helper function to validate coordinate integrity
            def is_valid_box(box):
                if isinstance(box, (list, tuple)) and len(box) >= 4:
                    # Format: [x1, y1, x2, y2]
                    return (box[2] - box[0]) > 0 and (box[3] - box[1]) > 0
                elif isinstance(box, dict):
                    # Format: {"x": 0, "y": 0, "w": 100, "h": 100} or with explicit keys
                    w = box.get("w") or box.get("width") or (box.get("x2", 0) - box.get("x1", 0))
                    h = box.get("h") or box.get("height") or (box.get("y2", 0) - box.get("y1", 0))
                    return float(w) > 0 and float(h) > 0
                return False

            # Deep validate zones inside front/back targets
            for side in ["front", "back"]:
                if side in parsed and isinstance(parsed[side], dict):
                    for zone_name, box in parsed[side].items():
                        if not is_valid_box(box):
                            raise forms.ValidationError(
                                _(f"Invalid dimensions detected in {side} zone '{zone_name}'. Width and height must be greater than 0.")
                            )

            return parsed
        except (ValueError, TypeError):
            return None

    def _validate_component(self, file):
        try:
            validate_upload(file)
        except (EmptyFileError, FileTooLargeError, UnsupportedFileTypeError) as e:
            raise forms.ValidationError(str(e))
        return file