from django import forms
from .models import AreaComun, Reserva


class AreaComunForm(forms.ModelForm):
    class Meta:
        model = AreaComun
        fields = ["nombre", "descripcion", "edificio", "capacidad_maxima", "horario_inicio", "horario_fin", "imagen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "edificio": forms.Select(attrs={"class": "form-select"}),
            "capacidad_maxima": forms.NumberInput(attrs={"class": "form-control"}),
            "horario_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "horario_fin": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ["area_comun", "residente", "fecha", "hora_inicio", "hora_fin", "estado", "motivo"]
        widgets = {
            "area_comun": forms.Select(attrs={"class": "form-select"}),
            "residente": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fin": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "motivo": forms.TextInput(attrs={"class": "form-control"}),
        }
