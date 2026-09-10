import io
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import (
    Einladung,
    FragebogenFall,
    FragebogenAntwort,
    FragebogenAbschnitt,
    AbschnittAntwort,
    FrageAntwort,
    Kategorie,
)
from .forms import AbschnittForm
from .services import process_and_notify_pdf, build_evaluation_data, generate_radar_chart, generate_motivation_chart

def fragebogen_start(request, code):
    einladung = get_object_or_404(
        Einladung,
        code=code
    )

    return render(
        request,
        "fragebogen_start.html",
        {
            "fragebogen": einladung.fall.fragebogen,
            "einladung": einladung,
        }
    )


def abschnitt_ausfuellen(request, code, abschnitt_nr):
    einladung = get_object_or_404(
        Einladung,
        code=code
    )

    fragebogen = einladung.fall.fragebogen

    abschnitte = list(
        fragebogen.abschnitte.all()
        .order_by("reihenfolge")
    )

    abschnitt = get_object_or_404(
        FragebogenAbschnitt,
        fragebogen=fragebogen,
        reihenfolge=abschnitt_nr,
    )

    antwort, created = FragebogenAntwort.objects.get_or_create(
        einladung=einladung
    )

    abschnitt_antwort = (
        AbschnittAntwort.objects
        .filter(
            fragebogen_antwort=antwort,
            fragebogen_abschnitt=abschnitt,
        )
        .first()
    )

    if request.method == "POST":
        action = request.POST.get("action")

        form = AbschnittForm(
            request.POST,
            fragebogen_abschnitt=abschnitt,
            abschnitt_antwort=abschnitt_antwort,
        )

        # ==========================================
        # 1. HANDLE "BACK" ACTION
        # ==========================================
        if action == "back":
            if form.is_valid():
                abschnitt_antwort, created = (
                    AbschnittAntwort.objects.update_or_create(
                        fragebogen_antwort=antwort,
                        fragebogen_abschnitt=abschnitt,
                        defaults={
                            "kommentar": form.cleaned_data["kommentar"]
                        }
                    )
                )

                for frage in form.fragen:
                    FrageAntwort.objects.update_or_create(
                        abschnitt_antwort=abschnitt_antwort,
                        frage=frage,
                        defaults={
                            "antwort_wert": form.cleaned_data[f"frage_{frage.id}"]
                        }
                    )

            prev_section = max(1, abschnitt_nr - 1)
            return redirect(
                "abschnitt_ausfuellen",
                code=code,
                abschnitt_nr=prev_section,
            )

        # ==========================================
        # 2. HANDLE "NEXT" / SUBMIT ACTION
        # ==========================================
        if form.is_valid():
            abschnitt_antwort, created = (
                AbschnittAntwort.objects.update_or_create(
                    fragebogen_antwort=antwort,
                    fragebogen_abschnitt=abschnitt,
                    defaults={
                        "kommentar": form.cleaned_data["kommentar"]
                    }
                )
            )

            for frage in form.fragen:
                FrageAntwort.objects.update_or_create(
                    abschnitt_antwort=abschnitt_antwort,
                    frage=frage,
                    defaults={
                        "antwort_wert": form.cleaned_data[f"frage_{frage.id}"]
                    }
                )

            action = request.POST.get("action")

            if action == "back":
                return redirect(
                    "abschnitt_ausfuellen",
                    code=code,
                    abschnitt_nr=abschnitt_nr - 1,
                )

            if action == "next":
                next_section = abschnitt_nr + 1

                if next_section <= len(abschnitte):
                    return redirect(
                        "abschnitt_ausfuellen",
                        code=code,
                        abschnitt_nr=next_section,
                    )

                antwort.end_time = timezone.now()
                antwort.save()

                einladung.benutzt = True
                einladung.save()

                process_and_notify_pdf(einladung.fall, request)

                return redirect("success")

    else:
        form = AbschnittForm(
            fragebogen_abschnitt=abschnitt,
            abschnitt_antwort=abschnitt_antwort,
        )

    return render(
        request,
        "fragebogen.html",
        {
            "form": form,
            "fragebogen": fragebogen,
            "einladung": einladung,
            "abschnitt": abschnitt,
            "abschnitt_nr": abschnitt_nr,
            "gesamt_abschnitte": len(abschnitte),
        }
    )


def success(request):
    return render(
        request,
        "success.html"
    )


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def export_fragebogen_pdf(request, fall_id):
    fall = get_object_or_404(FragebogenFall, pk=fall_id)
    categories_list = build_evaluation_data(fall)

    radar_chart = generate_radar_chart(categories_list)
    motivation_chart = generate_motivation_chart(categories_list)

    selbst_einladung = fall.selbsteinschaetzung()
    fremd_einladung = fall.fremdeinschaetzung()

    selbsteinschaetzung = getattr(selbst_einladung, 'antwort', None) if selbst_einladung else None
    fremdeinschaetzung = getattr(fremd_einladung, 'antwort', None) if fremd_einladung else None

    context = {
        "fall": fall,
        "categories_list": categories_list,
        "radar_chart": radar_chart,
        "motivation_chart": motivation_chart,
        "selbsteinschaetzung": selbsteinschaetzung,
        "fremdeinschaetzung": fremdeinschaetzung,
    }

    html = render_to_string("auswertung_pdf.html", context)
    pdf = HTML(string=html).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="fragebogen_auswertung.pdf"'

    return response