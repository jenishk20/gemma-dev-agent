<?php

namespace App\Http\Controllers;

use App\Models\Entry;
use App\Models\Edit;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class WikiController extends Controller
{
    public function index()
    {
        $entries = Entry::all();
        $html = "<h1>Wiki Entries</h1><ul>";
        foreach ($entries as $entry) {
            $html .= "<li><a href='/entries/{$entry->id}'>{$entry->title}</a></li>";
        }
        $html .= "</ul><hr><form method='POST' action='/entries'><h2>Create Entry</h2>";
        $html .= "Title: <input name='title'><br>Content: <textarea name='content'></textarea><br>";
        $html .= "Author: <input name='createdBy'><br><button type='submit'>Create</button></form>";
        
        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'title' => 'required',
            'content' => 'required',
            'createdBy' => 'required'
        ]);

        $entry = Entry::create([
            'title' => $request->title,
            'content' => $request->content,
            'last_modified_by' => $request->createdBy
        ]);

        // Initial edit record
        Edit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modified_by' => $request->createdBy,
            'summary' => 'Initial creation'
        ]);

        return response()->json($entry, 201);
    }

    public function show($entryId)
    {
        $entry = Entry::findOrFail($entryId);
        $contributors = $entry->edits()->pluck('modified_by')->unique()->implode(', ');

        $html = "<h1>{$entry->title}</h1>";
        $html .= "<p>{$entry->content}</p>";
        $html .= "<p><i>Last modified by {$entry->last_modified_by} at {$entry->updated_at}</i></p>";
        $html .= "<p>Contributors: {$contributors}</p>";
        $html .= "<hr><a href='/entries/{$entryId}/edits'>View History</a> | ";
        $html .= "<a href='/entries/edit/{$entryId}'>Edit Page</a>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function update(Request $request, $entryId)
    {
        $entry = Entry::findOrFail($entryId);
        
        $this->validate($request, [
            'content' => 'required',
            'modifiedBy' => 'required',
            'summary' => 'required'
        ]);

        $entry->update([
            'content' => $request->content,
            'last_modified_by' => $request->modifiedBy
        ]);

        Edit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modified_by' => $request->modifiedBy,
            'summary' => $request->summary
        ]);

        return response()->json($entry, 200);
    }

    public function history($entryId)
    {
        $entry = Entry::findOrFail($entryId);
        $edits = Edit::where('entry_id', $entryId)->orderBy('created_at', 'desc')->get();

        $html = "<h1>History for {$entry->title}</h1><ul>";
        foreach ($edits as $edit) {
            $html .= "<li><strong>{$edit->modified_by}</strong> ({$edit->created_at}): {$edit->summary}<br>";
            $html .= "<pre>{$edit->content}</pre></li><hr>";
        }
        $html .= "</ul><a href='/entries/{$entryId}'>Back to entry</a>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    // Helper for the HTML UI to show an edit form
    public function editForm($entryId)
    {
        $entry = Entry::findOrFail($entryId);
        $html = "<h1>Edit {$entry->title}</h1>";
        $html .= "<form method='POST' action='/entries/{$entryId}'"; 
        // Note: Lumen/Laravel requires spoofing PUT via _method for HTML forms
        $html .= "><input type='hidden' name='_method' value='PUT'>";
        $html .= "Content: <textarea name='content'>{$entry->content}</textarea><br>";
        $html .= "Your Name: <input name='modifiedBy'><br>";
        $html .= "Summary of change: <input name='summary'><br>";
        $html .= "<button type='submit'>Save Changes</button></form>";
        
        return response($html, 200)->header('Content-Type', 'text/html');
    }
}