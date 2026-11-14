import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Entry, Edit

def entries_view(request):
    if request.method == 'GET':
        entries = Entry.objects.all()
        html = "<h1>Wiki Entries</h1><ul>"
        for e in entries:
            html += f'<li><a href="/entries/{e.id}">{e.title}</a></li>'
        html += "</ul><hr><p>Create new entry via POST /entries</p>"
        return HttpResponse(html)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry = Entry.objects.create(
                title=data['title'],
                content=data['content'],
                last_modified_by=data['createdBy']
            )
            # Record initial edit
            Edit.objects.create(
                entry=entry,
                content_snapshot=entry.content,
                modified_by=data['createdBy'],
                summary="Initial creation"
            )
            return JsonResponse({
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "lastModifiedBy": entry.last_modified_by,
                "lastModifiedAt": entry.last_modified_at.isoformat()
            }, status=201)
        except Exception as e:
            return HttpResponse(str(e), status=400)

def entry_detail_view(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    
    if request.method == 'GET':
        contributors = Edit.objects.filter(entry=entry).values_list('modified_by', flat=True).distinct()
        html = f"<h1>{entry.title}</h1>"
        html += f"<p>{entry.content}</p>"
        html += f"<p><b>Last Modified:</b> {entry.last_modified_at}<br>"
        html += f"<b>By:</b> {entry.last_modified_by}</p>"
        html += f"<p><b>Contributors:</b> {', '.join(contributors)}</p>"
        html += f'<hr><a href="/entries/{entry.id}/edits">View History</a>'
        return HttpResponse(html)
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            entry.content = data['content']
            entry.last_modified_by = data['modifiedBy']
            entry.save()
            
            Edit.objects.create(
                entry=entry,
                content_snapshot=data['content'],
                modified_by=data['modifiedBy'],
                summary=data['summary']
            )
            return JsonResponse({
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "lastModifiedBy": entry.last_modified_by,
                "lastModifiedAt": entry.last_modified_at.isoformat()
            })
        except Exception as e:
            return HttpResponse(str(e), status=400)

def entry_edits_view(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    edits = Edit.objects.filter(entry=entry).order_by('-modified_at')
    
    html = f"<h1>Edit History for {entry.title}</h1><ul>"
    for edit in edits:
        html += f"<li><b>{edit.modified_at}</b> by {edit.modified_by}: {edit.summary}<br>"
        html += f"<i>Content:</i> {edit.content_snapshot}</li><hr>"
    html += "</ul><a href='/entries/'>Back to Home</a>"
    return HttpResponse(html)

# Wrap views to disable CSRF for API testing
def api_wrapper(view_func):
    return csrf_exempt(view_func)

entries_view = api_wrapper(entries_view)
entry_detail_view = api_wrapper(entry_detail_view)
entry_edits_view = api_wrapper(entry_edits_view)