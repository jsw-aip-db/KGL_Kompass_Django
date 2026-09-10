import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import render_to_string
from weasyprint import HTML

import io
import base64
import numpy as np
import matplotlib.pyplot as plt

from .models import FragebogenAbschnitt

PASTEL_COLORS = [
    '#bddff7',  # Soft Blau
    '#fff2bd',  # Soft Gelb
    '#ebc2ff',  # Soft Violett
    '#b6ffd3',  # Soft Grün
    '#fdb8b2',  # Soft Rosa/Rot
    '#fadfb6',  # Soft Orange
    '#cbe4e4',  # Soft Grau
]

def build_evaluation_data(fall):
    selbst_einladung = fall.selbsteinschaetzung()
    fremd_einladung = fall.fremdeinschaetzung()

    selbst_antwort = getattr(selbst_einladung, 'antwort', None) if selbst_einladung else None
    fremd_antwort = getattr(fremd_einladung, 'antwort', None) if fremd_einladung else None

    selbst_scores = {}
    selbst_kommentare = {}
    if selbst_antwort:
        for aa in selbst_antwort.abschnitt_antworten.select_related('fragebogen_abschnitt').all():
            aid = aa.fragebogen_abschnitt_id
            selbst_kommentare[aid] = aa.kommentar
            for fa in aa.antworten.select_related('frage').all():
                selbst_scores[(aid, fa.frage.reihenfolge)] = fa.antwort_wert

    fremd_scores = {}
    fremd_kommentare = {}
    if fremd_antwort:
        for aa in fremd_antwort.abschnitt_antworten.select_related('fragebogen_abschnitt').all():
            aid = aa.fragebogen_abschnitt_id
            fremd_kommentare[aid] = aa.kommentar
            for fa in aa.antworten.select_related('frage').all():
                fremd_scores[(aid, fa.frage.reihenfolge)] = fa.antwort_wert

    abschnitte = (
        FragebogenAbschnitt.objects.filter(fragebogen=fall.fragebogen)
        .select_related('kategorie')
        .order_by('kategorie__id', 'reihenfolge')
    )

    categories_dict = {}
    cat_color_index = 0
    cat_color_map = {}

    for abschnitt in abschnitte:
        kat = abschnitt.kategorie
        kat_id = kat.id if kat else 0
        kat_titel = kat.titel if kat else "Allgemein"

        if kat_id not in cat_color_map:
            cat_color_map[kat_id] = PASTEL_COLORS[cat_color_index % len(PASTEL_COLORS)]
            cat_color_index += 1

        if kat_id not in categories_dict:
            categories_dict[kat_id] = {
                'id': kat_id,
                'titel': kat_titel,
                'color': cat_color_map[kat_id],
                'items': []
            }

        aid = abschnitt.id
        item = {
            'abschnitt_id': aid,
            'title': abschnitt.titel,
            'selbst_komp': selbst_scores.get((aid, 1)),
            'fremd_komp': fremd_scores.get((aid, 1)),
            'selbst_motiv': selbst_scores.get((aid, 2)),
            'fremd_motiv': fremd_scores.get((aid, 2)),
            'selbst_kommentar': selbst_kommentare.get(aid, ""),
            'fremd_kommentar': fremd_kommentare.get(aid, ""),
        }
        categories_dict[kat_id]['items'].append(item)

    return list(categories_dict.values())

def generate_radar_chart(categories_list):
    labels = []
    selbst_vals = []
    fremd_vals = []
    cat_bounds = []

    current_idx = 0
    for cat in categories_list:
        start = current_idx
        for item in cat['items']:
            title = item['title'].replace(" & ", " &\n")
            labels.append(title)
            selbst_vals.append(item['selbst_komp'] if item['selbst_komp'] is not None else 0)
            fremd_vals.append(item['fremd_komp'] if item['fremd_komp'] is not None else 0)
            current_idx += 1
        end = current_idx
        if start < end:
            cat_bounds.append((start, end, cat['titel'], cat['color']))

    num_vars = len(labels)
    if num_vars == 0:
        return None

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    selbst_closed = selbst_vals + [selbst_vals[0]]
    fremd_closed = fremd_vals + [fremd_vals[0]]
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw=dict(polar=True))

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    label_radius = 7.2
    for angle, label in zip(angles, labels):
        norm_angle = angle % (2 * np.pi)

        if np.isclose(norm_angle, 0, atol=0.1):
            ha, va = 'center', 'bottom'
        elif np.isclose(norm_angle, np.pi, atol=0.1):
            ha, va = 'center', 'top'
        elif 0 < norm_angle < np.pi:
            ha, va = 'left', 'center'
        else:
            ha, va = 'right', 'center'

        ax.text(
            angle, label_radius, label,
            size=7.2,
            ha=ha, va=va,
            clip_on=False
        )

    angle_step = (2 * np.pi) / num_vars
    for start, end, cat_title, color in cat_bounds:
        theta_start = start * angle_step - (angle_step / 2)
        theta_end = (end - 1) * angle_step + (angle_step / 2)

        sector_theta = np.linspace(theta_start, theta_end, 100)
        ax.fill_between(sector_theta, 0, 7, color=color, alpha=0.2, zorder=1)

        mid_theta = (theta_start + theta_end) / 2
        norm_mid = mid_theta % (2 * np.pi)

        if cat_title in ['Zukunftskompetenz', 'Sozialkompetenz']:
            r_badge = 9.4
            va_b = 'bottom'
        else:
            r_badge = 8.5
            y_dir = np.cos(norm_mid)
            va_b = 'bottom' if y_dir >= -0.2 else 'top'

        ax.text(
            mid_theta, r_badge, cat_title,
            ha='center', va=va_b, fontsize=8.0, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.25', facecolor=color, edgecolor='none', alpha=0.9),
            clip_on=False
        )

    ax.set_rlim(0, 7)
    ax.set_rticks([1, 2, 3, 4, 5, 6, 7])
    ax.set_yticklabels(['1', '2', '3', '4', '5', '6', '7'], color='gray', size=6.5)

    ax.plot(angles_closed, selbst_closed, color='#1f77b4', linewidth=1.6, linestyle='solid', label='Selbst', zorder=3)
    ax.scatter(angles, selbst_vals, color='#1f77b4', s=22, zorder=4)

    ax.plot(angles_closed, fremd_closed, color='#d62728', linewidth=1.6, linestyle='solid', label='Fremd', zorder=3)
    ax.scatter(angles, fremd_vals, color='#d62728', s=22, marker='s', zorder=4)

    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.12), fontsize=8.0, frameon=True)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def generate_motivation_chart(categories_list):
    y_labels = []
    selbst_motiv_vals = []
    fremd_motiv_vals = []
    cat_spans = []

    current_idx = 0
    for cat in categories_list:
        start = current_idx
        for item in cat['items']:
            y_labels.append(item['title'])
            selbst_motiv_vals.append(item['selbst_motiv'] if item['selbst_motiv'] is not None else 0)
            fremd_motiv_vals.append(item['fremd_motiv'] if item['fremd_motiv'] is not None else 0)
            current_idx += 1
        end = current_idx
        if start < end:
            cat_spans.append((start, end, cat['titel'], cat['color']))

    num_items = len(y_labels)
    if num_items == 0:
        return None

    fig_height = max(1.8, num_items * 0.3 + 0.6)
    fig, ax = plt.subplots(figsize=(4.8, fig_height))

    y_positions = np.arange(num_items)
    bar_height = 0.30

    for start, end, cat_title, color in cat_spans:
        y_bottom = start - 0.45
        y_top = end - 0.55
        ax.axhspan(y_bottom, y_top, color=color, alpha=0.25, zorder=0)

    bars_selbst = ax.barh(
        y_positions - bar_height / 2,
        selbst_motiv_vals,
        height=bar_height,
        color='#1f77b4',
        label='Selbsteinschätzung',
        zorder=2
    )

    bars_fremd = ax.barh(
        y_positions + bar_height / 2,
        fremd_motiv_vals,
        height=bar_height,
        color='#d62728',
        label='Fremdeinschätzung',
        zorder=2
    )

    for bar in bars_selbst:
        width = bar.get_width()
        if width > 0:
            ax.text(width + 0.12, bar.get_y() + bar.get_height() / 2, f'{int(width)}',
                    va='center', ha='left', fontsize=6.5, color='#1f77b4', fontweight='bold')

    for bar in bars_fremd:
        width = bar.get_width()
        if width > 0:
            ax.text(width + 0.12, bar.get_y() + bar.get_height() / 2, f'{int(width)}',
                    va='center', ha='left', fontsize=6.5, color='#d62728', fontweight='bold')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 7.8)
    ax.set_xticks([1, 2, 3, 4, 5, 6, 7])
    ax.set_xlabel('Motivation (1 = niedrig ... 7 = extrem hoch)', fontsize=6.5)

    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=6.5, frameon=False)
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=180, bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def process_and_notify_pdf(fall, request=None):
    # 1. Render PDF binary with WeasyPrint
    categories_list = build_evaluation_data(fall)
    html = render_to_string("auswertung_pdf.html", {
        "fall": fall,
        "categories_list": categories_list,
        "radar_chart": generate_radar_chart(categories_list),
        "motivation_chart": generate_motivation_chart(categories_list),
    })
    pdf_bytes = HTML(string=html).write_pdf()

    # 2. Save via default_storage (Saves to media/ folder in dev, S3 in prod)
    file_path = f"auswertungen/fall_{fall.id}_auswertung.pdf"
    saved_path = default_storage.save(file_path, ContentFile(pdf_bytes))

    # 3. Build access link
    pdf_url = default_storage.url(saved_path)
    if settings.DEBUG and request:
        pdf_url = request.build_absolute_uri(pdf_url)

    # 4. Email dispatch (Prints to terminal when DEBUG=True)
    fremd = fall.fremdeinschaetzung()
    if fremd and fremd.bezugsperson:
        send_mail(
            subject=f"Auswertung verfügbar: {fall.jugendliche_person}",
            message=f"Die Auswertung ist fertig. Hier abrufen: {pdf_url}",
            from_email="noreply@domain.local",
            recipient_list=[fremd.bezugsperson.email],
        )

    # 5. Send Webhook
    if settings.TEAMS_WEBHOOK_URL:
        payload = {
            "text": f"Auswertung fertiggestellt für **{fall.jugendliche_person}**.\n\n[PDF Downloaden]({pdf_url})"
        }
        try:
            requests.post(settings.TEAMS_WEBHOOK_URL, json=payload, timeout=5)
        except Exception as e:
            print(f"Webhook notification failed: {e}")