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
            $html .= "<li><a href='/entries/{$entry->id}'>{$entry->title}</a></li>";
        }
        $html .= "</ul><hr><a href='/entries/new'>Create New Entry</a>";
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

        return response()->json($entry, 201);
    }

    public function show($id)
    {
        $entry = Entry::findOrFail($id);
        $contributors = EntryEdit::where('entry_id', $id)->pluck('modified_by')->unique()->implode(', ');

        $html = "<h1>{$entry->title}</h1>";
        $html .= "<p>{$entry->content}</p>";
        $html .= "<hr><p><i>Last modified by {$entry->last_modified_by} at {$entry->updated_at}</i></p>";
        $html .= "<p><b>Contributors:</b> {$contributors}</p>";
        $html .= "<a href='/entries/{$id}/edits'>View History</a> | ";
        $html .= "<a href='/entries'>Back to List</a>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function update(Request $request, $id)
    {
        $entry = Entry::findOrFail($id);
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

        return response()->json($entry, 200);
    }

    public function history($id)
    {
        $entry = Entry::findOrFail($id);
        $edits = EntryEdit::where('entry_id', $id)->orderBy('created_at', 'desc')->get();

        $html = "<h1>History for {$entry->title}</h1><ul>";
        foreach ($edits as $edit) {
            $html .= "<li><b>{$edit->created_at}</b> by {$edit->modified_by}: {$edit->summary}<br>";
            $html .= "<pre>{$edit->content}</pre></li><hr>";
        }
        $html .= "</ul><a href='/entries/{$id}'>Back to Entry</a>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}