<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Entry;
use App\Models\EntryEdit;

class WikiController extends Controller
{
    public function index()
    {
        $entries = Entry::all();
        $html = "<h1>Wiki Entries</h1><ul>";
        foreach ($entries as $entry) {
            $html .= "<li><a href='/entries/{$entry->id}'>" . htmlspecialchars($entry->title) . "</a></li>";
        }
        $html .= "</ul><hr><p>Create new entry via POST /entries</p>";
        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'title' => 'required|string',
            'content' => 'required|string',
            'createdBy' => 'required|string',
        ]);

        $entry = Entry::create([
            'title' => $request->title,
            'content' => $request->content,
            'last_modified_by' => $request->createdBy,
        ]);

        // Initial version
        EntryEdit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modified_by' => $request->createdBy,
            'summary' => 'Initial creation',
        ]);

        return response()->json([
            'id' => $entry->id,
            'title' => $entry->title,
            'content' => $entry->content,
            'lastModifiedBy' => $entry->last_modified_by,
            'lastModifiedAt' => $entry->updated_at->toIso8601String(),
        ], 201);
    }

    public function show($entryId)
    {
        $entry = Entry::findOrFail($entryId);
        $contributors = EntryEdit::where('entry_id', $entryId)->pluck('modified_by')->unique();

        $html = "<h1>" . htmlspecialchars($entry->title) . "</h1>";
        $html .= "<div>" . nl2br(htmlspecialchars($entry->content)) . "</div>";
        $html .= "<p><i>Last modified by {$entry->last_modified_by} on {$entry->updated_at}</i></p>";
        $html .= "<h3>Contributors:</h3><ul>";
        foreach ($contributors as $user) {
            $html .= "<li>" . htmlspecialchars($user) . "</li>";
        }
        $html .= "</ul>";
        $html .= "<p><a href='/entries/{$entryId}/edits'>View History</a></p>";
        $html .= "<p><a href='/entries'>Back to Home</a></p>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function update(Request $request, $entryId)
    {
        $entry = Entry::findOrFail($entryId);

        $this->validate($request, [
            'content' => 'required|string',
            'modifiedBy' => 'required|string',
            'summary' => 'required|string',
        ]);

        $entry->update([
            'content' => $request->content,
            'last_modified_by' => $request->modifiedBy,
        ]);

        EntryEdit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modified_by' => $request->modifiedBy,
            'summary' => $request->summary,
        ]);

        return response()->json([
            'id' => $entry->id,
            'title' => $entry->title,
            'content' => $entry->content,
            'lastModifiedBy' => $entry->last_modified_by,
            'lastModifiedAt' => $entry->updated_at->toIso8601String(),
        ], 200);
    }

    public function history($entryId)
    {
        $entry = Entry::findOrFail($entryId);
        $edits = EntryEdit::where('entry_id', $entryId)->orderBy('created_at', 'desc')->get();

        $html = "<h1>History for " . htmlspecialchars($entry->title) . "</h1><ul>";
        foreach ($edits as $edit) {
            $html .= "<li>";
            $html .= "<strong>{$edit->modified_by}</strong>: {$edit->summary} ({$edit->created_at})";
            $html .= "<pre>" . htmlspecialchars($edit->content) . "</pre>";
            $html .= "</li><hr>";
        }
        $html .= "</ul><p><a href='/entries/{$entryId}'>Back to Entry</a></p>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}