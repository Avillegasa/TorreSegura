from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import AreaComun, Reserva
from .forms import AreaComunForm, ReservaForm


class GerenteSoloMixin(UserPassesTestMixin):
    """Solo gerentes pueden acceder. Cada gerente ve unicamente su edificio."""

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        rol = getattr(getattr(user, "rol", None), "nombre", None)
        return rol == "Gerente" and hasattr(user, "gerente") and user.gerente and user.gerente.edificio

    def handle_no_permission(self):
        messages.error(self.request, "Solo los gerentes de edificio pueden acceder a esta seccion.", extra_tags="danger")
        return redirect("dashboard")

    def get_edificio(self):
        return self.request.user.gerente.edificio


# --- Areas Comunes ---

class AreaComunListView(LoginRequiredMixin, GerenteSoloMixin, ListView):
    model = AreaComun
    template_name = "areas_comunes/area_comun_list.html"
    context_object_name = "areas"

    def get_queryset(self):
        return (
            AreaComun.objects.filter(edificio=self.get_edificio())
            .select_related("edificio")
        )


class AreaComunCreateView(LoginRequiredMixin, GerenteSoloMixin, CreateView):
    model = AreaComun
    form_class = AreaComunForm
    template_name = "areas_comunes/area_comun_form.html"
    success_url = reverse_lazy("area-comun-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Forzar solo el edificio del gerente
        edificio = self.get_edificio()
        form.fields["edificio"].queryset = edificio.__class__.objects.filter(pk=edificio.pk)
        form.fields["edificio"].initial = edificio
        return form

    def form_valid(self, form):
        form.instance.edificio = self.get_edificio()
        messages.success(self.request, "Area comun creada exitosamente.")
        return super().form_valid(form)


class AreaComunUpdateView(LoginRequiredMixin, GerenteSoloMixin, UpdateView):
    model = AreaComun
    form_class = AreaComunForm
    template_name = "areas_comunes/area_comun_form.html"
    success_url = reverse_lazy("area-comun-list")

    def get_queryset(self):
        return AreaComun.objects.filter(edificio=self.get_edificio())

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        edificio = self.get_edificio()
        form.fields["edificio"].queryset = edificio.__class__.objects.filter(pk=edificio.pk)
        return form

    def form_valid(self, form):
        form.instance.edificio = self.get_edificio()
        messages.success(self.request, "Area comun actualizada exitosamente.")
        return super().form_valid(form)


class AreaComunDeleteView(LoginRequiredMixin, GerenteSoloMixin, DeleteView):
    model = AreaComun
    template_name = "areas_comunes/area_comun_confirm_delete.html"
    success_url = reverse_lazy("area-comun-list")

    def get_queryset(self):
        return AreaComun.objects.filter(edificio=self.get_edificio())

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Area comun eliminada exitosamente.")
        return super().delete(request, *args, **kwargs)


class AreaComunDetailView(LoginRequiredMixin, GerenteSoloMixin, DetailView):
    model = AreaComun
    template_name = "areas_comunes/area_comun_detail.html"
    context_object_name = "area"

    def get_queryset(self):
        return AreaComun.objects.filter(edificio=self.get_edificio())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reservas"] = (
            Reserva.objects.filter(area_comun=self.object)
            .select_related("residente__usuario")
            .order_by("-fecha", "-hora_inicio")[:20]
        )
        return context


# --- Reservas ---

class ReservaListView(LoginRequiredMixin, GerenteSoloMixin, ListView):
    model = Reserva
    template_name = "areas_comunes/reserva_list.html"
    context_object_name = "reservas"

    def get_queryset(self):
        return (
            Reserva.objects.filter(area_comun__edificio=self.get_edificio())
            .select_related("area_comun", "residente__usuario")
            .order_by("-fecha", "-hora_inicio")[:100]
        )


class ReservaDeleteView(LoginRequiredMixin, GerenteSoloMixin, DeleteView):
    model = Reserva
    template_name = "areas_comunes/reserva_confirm_delete.html"
    success_url = reverse_lazy("reserva-list")

    def get_queryset(self):
        return Reserva.objects.filter(area_comun__edificio=self.get_edificio())

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Reserva eliminada exitosamente.")
        return super().delete(request, *args, **kwargs)
