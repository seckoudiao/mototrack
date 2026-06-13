from django import forms

from .models import Affectation, Livreur, Mission, Moto


class BootstrapFormMixin:
    """Ajoute automatiquement les classes Bootstrap aux champs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class LivreurForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Livreur
        fields = ["user", "nom", "prenom", "telephone", "adresse", "cni", "numero_permis", "photo", "statut"]


class MotoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Moto
        fields = ["immatriculation", "marque", "modele", "etat"]


class AffectationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Affectation
        fields = ["livreur", "moto", "date_debut", "date_fin", "active"]
        widgets = {
            "date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "date_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class MissionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Mission
        fields = [
            "client_nom",
            "client_telephone",
            "adresse_livraison",
            "description_lieu",
            "description_colis",
            "latitude_destination",
            "longitude_destination",
            "livreur",
            "moto",
            "statut",
        ]
        widgets = {
            "latitude_destination": forms.HiddenInput(),
            "longitude_destination": forms.HiddenInput(),
            "description_lieu": forms.Textarea(attrs={"rows": 3}),
            "description_colis": forms.Textarea(attrs={"rows": 3}),
        }


class OTPValidationForm(BootstrapFormMixin, forms.Form):
    otp_code = forms.CharField(label="Code OTP", max_length=6, min_length=6)
    latitude_validation = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude_validation = forms.FloatField(required=False, widget=forms.HiddenInput())
