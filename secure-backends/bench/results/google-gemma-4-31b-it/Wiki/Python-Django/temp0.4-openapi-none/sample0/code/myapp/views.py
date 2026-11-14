import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Entry, Edit
from django.utils import timezone

@csrf_exempt
def entries_view(request, entryId=None):
    if entryId is None:
        # /entries
        if request.method == 'GET':
            entries = Entry.objects.all()
            html = "<h1>Wiki Entries</h1><ul>"
            for e in entries:
                html += f'<li><a href="/entries/{e.id}">{e.title}</a></li>'
            html += "</ul><hr><a href='/entries'>Create New Entry</a>"
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

    else:
        # /entries/{entryId}
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
            <hr>
            <a href="/entries/{entry.id}/edits">View History</a> | 
            <form method="POST" action="/update/{entry.id}" style="display:inline">
                <input type="text" name="summary" placeholder="Edit summary" required>
                <textarea name="content">{entry.content}</textarea>
                <input type="text" name="user" placeholder="Your name" required>
                <button type="submit">Update</button>
            </form>
            """
            # Note: The schema asks for PUT for updates. Since HTML forms only do GET/POST, 
            # we handle the logic in a separate helper or just use the API.
            # To strictly follow the OpenAPI schema for the API part:
            return HttpResponse(html)

        elif request.method == 'PUT':
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
                
                # Save the new edit
                Edit.objects.create(
                    entry=entry,
                    content_snapshot=entry.content,
                    modified_by=data['modifiedBy'],
                    summary=data.get('summary', 'Updated')
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

@csrf_exempt
def update_helper(request, entryId):
    """Helper for HTML form updates since forms don't support PUT"""
    if request.method == 'POST':
        entry = get_object_or_404(Entry, pk=entryId)
        content = request.POST.get('content')
        user = request.POST.get('user')
        summary = request.POST.get('summary')
        
        # Record history
        Edit.objects.create(
            entry=entry,
            content_snapshot=entry.content,
            modified_by=entry.last_modified_by,
            summary="Reverted/Previous"
        )
        
        entry.content = content
        entry.last_modified_by = user
        entry.save()
        
        Edit.objects.create(
            entry=entry,
            content_snapshot=content,
            modified_by=user,
            summary=summary
        )
        return HttpResponse("Updated successfully. <a href='/entries/%s' />" % entryId)

def edits_view(request, entryId):
    entry = get_object_or_404(Entry, pk=entryId)
    edits = Edit.objects.filter(entry=entry).order_by('-timestamp')
    
    html = f"<h1>Edit History for {entry.title}</h1><ul>"
    for i in range(len(edits)):
        edit = edits[i]
        html += f"<li><b>{edit.modified_by}</b> ({edit.timestamp}): {edit.summary}<br><pre>{edit.content_snapshot}</pre></li>"
    html += "</ul><a href='/entries/{}'>Back to entry</a>".format(entryId)
    return HttpResponse(html)