import json
import re

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ungettext, ugettext_lazy as _

import requests

from wagtail.admin import messages
from wagtail.core.models import Page

from wagtailimportexport.exporting import export_pages
from wagtailimportexport.forms import ExportForm, ImportFromAPIForm, ImportFromFileForm
from wagtailimportexport.importing import import_pages


def index(request):
    return render(request, 'wagtailimportexport/index.html')


def import_from_api(request):
    if request.method == 'POST':
        form = ImportFromAPIForm(request.POST)
        if form.is_valid():
            # remove trailing slash from base url
            base_url = re.sub(r'\/$', '', form.cleaned_data['source_site_base_url'])
            import_url = (
                base_url + reverse('wagtailimportexport:export', args=[form.cleaned_data['source_page_id']])
            )
            r = requests.get(import_url)
            import_data = r.json()
            parent_page = form.cleaned_data['parent_page']

            page_count = import_pages(import_data, parent_page)

            page_count = len(import_data['pages'])
            messages.success(request, ungettext(
                "%(count)s page imported.",
                "%(count)s pages imported.",
                page_count) % {'count': page_count}
            )
            return redirect('wagtailadmin_explore', parent_page.pk)
    else:
        form = ImportFromAPIForm()

    return render(request, 'wagtailimportexport/import_from_api.html', {
        'form': form,
    })


def import_from_file(request):
    if request.method == 'POST':
        form = ImportFromFileForm(request.POST, request.FILES)
        if form.is_valid():
            parent_page = form.cleaned_data['parent_page']
            import_data = json.loads(form.cleaned_data['file'].read().decode('utf-8'))

            page_count = import_pages(import_data, parent_page)

            page_count = len(import_data['pages'])
            messages.success(request, ungettext(
                "%(count)s page imported.",
                "%(count)s pages imported.",
                page_count) % {'count': page_count}
            )
            return redirect('wagtailadmin_explore', parent_page.pk)
    else:
        form = ImportFromFileForm()

    return render(request, 'wagtailimportexport/import_from_file.html', {
        'form': form,
    })


def export_to_file(request):
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            payload = export_pages(form.cleaned_data['root_page'], export_unpublished=True)
            response = JsonResponse(payload)
            response['Content-Disposition'] = 'attachment; filename="export.json"'
            return response
    else:
        form = ExportForm()

    return render(request, 'wagtailimportexport/export_to_file.html', {
        'form': form,
    })


def export(request, page_id, export_unpublished=False):
    try:
        if export_unpublished:
            root_page = Page.objects.get(id=page_id)
        else:
            root_page = Page.objects.get(id=page_id, live=True)
    except Page.DoesNotExist:
        return JsonResponse({'error': _('page not found')})

    payload = export_pages(root_page, export_unpublished=export_unpublished)

    return JsonResponse(payload)
