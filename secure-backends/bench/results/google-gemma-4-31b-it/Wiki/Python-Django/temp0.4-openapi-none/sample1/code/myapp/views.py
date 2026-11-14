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
        html += "</ul><hr><form method='POST' action='/entries'><input name='title' placeholder='Title'><br><textarea name='content'></textarea><br><input name='createdBy' placeholder='Your Name'><br><button type='submit'>Create Entry</button></form>"
        return HttpResponse(html)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry = Entry.objects.create(
                title=data['title'],
                content=data['content'],
                last_modified_by=data['createdBy']
            )
            # Create initial edit record
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
        except (json.JSONDecodeError, KeyError):
            return HttpResponse("Invalid input", status=400)

def entry_detail_view(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)

    if request.method == 'GET':
        contributors = Edit.objects.filter(entry=entry).values_list('modified_by', flat=True).distinct()
        contrib_list = ", ".join(contributors)
        html = f"""
        <h1>{entry.title}</h1>
        <p>{entry.content}</p>
        <hr>
        <p>Last modified by: {entry.last_modified_by} at {entry.last_modified_at}</p>
        <p>Contributors: {contrib_list}</p>
        <a href="/entries/{entry.id}/edits">View History</a><br>
        <a href="/entries">Back to list</a>
        """
        return HttpResponse(html)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            # Save current state to history before updating
            Edit.objects.create(
                entry=entry,
                content_snapshot=entry.content,
                modified_by=entry.last_modified_by,
                summary="Previous version"
            )
            entry.content = data['content']
            entry.last_modified_by = data['modifiedBy']
            entry.save()
            
            # Log the new edit
            Edit.objects.create(
                entry=entry,
                content_snapshot=data['content'],
                modified_by=data['modifiedBy'],
                summary=data.get('summary', 'No summary')
            )
            
            return JsonResponse({
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "lastModifiedBy": entry.last_modified_by,
                "lastModifiedAt": entry.last_modified_at.isoformat()
            })
        except (json.JSONDecodeError, KeyError):
            return HttpResponse("Invalid input", status=400)

def entry_edits_view(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    edits = Edit.objects.filter(entry=entry).order_by('-created_at')
    
    html = f"<h1>History for {entry.title}</h1><ul>"
    for i in range(len(edits)):
        edit = edits[i]
        # Simple diff simulation: just show the content of that version
        html += f"<li><b>{edit.modified_by}</b> ({edit.created_at}): {edit.summary}<br><pre>{edit.content_snapshot}</pre></li>"
    html += "</ul><a href='/entries'>Back to list</a>"
    return HttpResponse(html)

# Decorate views to disable CSRF for the API endpoints
from django.views.decorators.csrf import csrf_exempt
entries_view = csrf_exempt(entries_view)
entry_detail_view = csrf_exempt(entry_detail_view)
entry_edits_view = csrf_exempt(entry_edits_view)