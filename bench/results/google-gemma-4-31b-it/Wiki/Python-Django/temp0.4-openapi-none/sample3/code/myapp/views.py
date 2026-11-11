import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import WikiEntry, WikiEdit

def entry_list_create(request):
    if request.method == 'GET':
        entries = WikiEntry.objects.all()
        html = "<h1>Wiki Entries</h1><ul>"
        for e in entries:
            html += f'<li><a href="/entries/{e.id}">{e.title}</a></li>'
        html += "</ul><hr><form method='POST' action='/entries'>"
        html += "Title: <input name='title'><br>Content: <textarea name='content'></textarea><br>User: <input name='createdBy'><br><input type='submit'></form>"
        return HttpResponse(html)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            # Fallback for form data
            data = {
                'title': request.POST.get('title'),
                'content': request.POST.get('content'),
                'createdBy': request.POST.get('createdBy')
            }
        
        entry = WikiEntry.objects.create(
            title=data['title'],
            content=data['content'],
            last_modified_by=data['createdBy']
        )
        # Initial edit record
        WikiEdit.objects.create(
            entry=entry,
            content_snapshot=data['content'],
            modified_by=data['createdBy'],
            summary="Initial creation"
        )
        return JsonResponse({
            'id': str(entry.id),
            'title': entry.title,
            'content': entry.content,
            'lastModifiedBy': entry.last_modified_by,
            'lastModifiedAt': entry.last_modified_at.isoformat()
        }, status=201)

@csrf_exempt
def entry_detail_update(request, entryId):
    entry = get_object_or_404(WikiEntry, pk=entryId)
    
    if request.method == 'GET':
        contributors = entry.edits.values_list('modified_by', flat=True).distinct()
        html = f"<h1>{entry.title}</h1>"
        html += f"<div>{entry.content}</div>"
        html += f"<p>Last edited by {entry.last_modified_by} on {entry.last_modified_at}</p>"
        html += f"<p>Contributors: {', '.join(contributors)}</p>"
        html += f'<hr><a href="/entries/{entry.id}/edits">View History</a>'
        return HttpResponse(html)
    
    if request.method == 'PUT':
        data = json.loads(request.body)
        entry.content = data['content']
        entry.last_modified_by = data['modifiedBy']
        entry.save()
        
        WikiEdit.objects.create(
            entry=entry,
            content_snapshot=data['content'],
            modified_by=data['modifiedBy'],
            summary=data.get('summary', 'No summary provided')
        )
        
        return JsonResponse({
            'id': str(entry.id),
            'title': entry.title,
            'content': entry.content,
            'lastModifiedBy': entry.last_modified_by,
            'lastModifiedAt': entry.last_modified_at.isoformat()
        })

def entry_history(request, entryId):
    entry = get_object_or_404(WikiEntry, pk=entryId)
    edits = WikiEdit.objects.filter(entry=entry).order_by('-modified_at')
    
    html = f"<h1>History for {entry.title}</h1><ul>"
    for edit in edits:
        html += f"<li><b>{edit.modified_by}</b> ({edit.modified_at}): {edit.summary}<br>"
        html += f"<code>{edit.content_snapshot}</code></li><hr>"
    html += "</ul><a href='/entries/'>Back to list</a>"
    return HttpResponse(html)