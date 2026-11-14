import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Entry, Edit

def entries_list_create(request):
    if request.method == 'GET':
        entries = Entry.objects.all()
        html = "<h1>Wiki Entries</h1><ul>"
        for e in entries:
            html += f'<li><a href="/entries/{e.id}">{e.title}</a></li>'
        html += "</ul><hr><p>To create a new entry, send a POST request with JSON.</p>"
        return HttpResponse(html)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry = Entry.objects.create(
                title=data['title'],
                content=data['content'],
                last_modified_by=data['createdBy']
            )
            # Initial edit record
            Edit.objects.create(
                entry=entry,
                content_snapshot=data['content'],
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
            return JsonResponse({"error": str(e)}, status=400)

def entry_detail_update(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    
    if request.method == 'GET':
        contributors = Edit.objects.filter(entry=entry).values_list('modified_by', flat=True).distinct()
        contrib_list = ", ".join(contributors)
        html = f"""
        <h1>{entry.title}</h1>
        <p><strong>Last Modified:</strong> {entry.last_modified_at} by {entry.last_modified_by}</p>
        <p><strong>Contributors:</strong> {contrib_list}</p>
        <hr>
        <div>{entry.content}</div>
        <hr>
        <a href="/entries/{entry.id}/edits">View History</a> | <a href="/entries">Back to List</a>
        """
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
            return JsonResponse({"error": str(e)}, status=400)

def entry_history(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    edits = Edit.objects.filter(entry=entry).order_by('-modified_at')
    
    html = f"<h1>History for {entry.title}</h1><ul>"
    for i in range(len(edits)):
        edit = edits[i]
        # Simple diff representation: just show the snapshot
        html += f"<li><strong>{edit.modified_at}</strong> - {edit.modified_by}: {edit.summary}<br>"
        html += f"<pre>{edit.content_snapshot}</pre></li><hr>"
    html += "</ul><a href='/entries/{entryId}'>Back to Entry</a>"
    return HttpResponse(html.replace('{entryId}', str(entryId)))