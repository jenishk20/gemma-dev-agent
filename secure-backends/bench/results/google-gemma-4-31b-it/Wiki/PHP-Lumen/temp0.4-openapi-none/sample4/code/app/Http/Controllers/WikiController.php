<?php

namespace App\Http\Controllers;

use App\Models\Entry;
use App\Models\Edit;
use Illuminate\Http\Request;

class WikiController extends Controller
{
    public function index()
    {
        $entries = Entry::all();
        $html = "<h1>Wiki Entries</h1><ul>";
        foreach ($entries as $entry) {
            $html .= "<li><a href='/entries/{$entry->id}'>{$entry->title}</a></li>";
        }
        $html .= "</ul><hr><p>Create new entry via POST /entries</p>";
        return response($html)->header('Content-Type', 'text/html');
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

        Edit::create([
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

    public function show($id)
    {
        $entry = Entry::findOrFail($id);
        $contributors = Edit::where('entry_id', $id)->pluck('modified_by')->unique()->implode(', ');

        $html = "<h1>{$entry->title}</h1>";
        $html .= "<p><strong>Last Modified:</strong> {$entry->updated_at} by {$entry->last_modified_by}</p>";
        $html .= "<p><strong>Contributors:</strong> {$contributors}</p>";
        $html .= "<div>{$entry->content}</div>";
        $html .= "<hr><a href='/entries/{$id}/edits'>View History</a>";
        
        return response($html)->header('Content-Type', 'text/html');
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

        Edit::create([
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
        ]);
    }

    public function history($id)
    {
        $entry = Entry::findOrFail($id);
        $edits = Edit::where('entry_id', $id)->orderBy('created_at', 'asc')->get();

        $html = "<h1>History for {$entry->title}</h1><ul>";
        foreach ($edits as $index => $edit) {
            $prevContent = ($index > 0) ? $edits[$index-1]->content : "[Empty]";
            $html .= "<li>";
            $html .= "<strong>User:</strong> {$edit->modified_by} | <strong>Date:</strong> {$edit->created_at}<br>";
            $html .= "<strong>Summary:</strong> {$edit->summary}<br>";
            $html .= "<strong>Diff:</strong><br>";
            $html .= "<pre style='background:#eee; padding:5px;'>- {$prevContent}\n+ {$edit->content}</pre>";
            $html .= "</li><hr>";
        }
        $html .= "</ul><a href='/entries/{$id}'>Back to entry</a>";

        return response($html)->header('Content-Type', 'text/html');
    }
}