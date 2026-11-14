<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Entry;
use App\Models\WikiEdit;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

class WikiController extends Controller
{
    public function __construct()
    {
        // Ensure tables exist for the demo purpose since we can't run migrations manually
        if (!Schema::hasTable('entries')) {
            Schema::create('entries', function ($table) {
                $table->id();
                $table->string('title');
                $table->text('content');
                $table->string('lastModifiedBy');
                $table->timestamp('lastModifiedAt')->useCurrent();
                $table->timestamps();
            });
        }
        if (!Schema::hasTable('wiki_edits')) {
            Schema::create('wiki_edits', function ($table) {
                $table->id();
                $table->foreignId('entry_id');
                $table->text('content');
                $table->string('modifiedBy');
                $table->string('summary');
                $table->timestamps();
            });
        }
    }

    public function index()
    {
        $entries = Entry::all();
        $html = "<h1>Wiki Entries</h1><ul>";
        foreach ($entries as $entry) {
            $html .= "<li><a href='/entries/{$entry->id}'>{$entry->title}</a></li>";
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
            'lastModifiedBy' => $request->createdBy,
            'lastModifiedAt' => now(),
        ]);

        WikiEdit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modifiedBy' => $request->createdBy,
            'summary' => 'Initial creation',
        ]);

        return response()->json($entry, 201);
    }

    public function show($id)
    {
        $entry = Entry::findOrFail($id);
        $contributors = WikiEdit::where('entry_id', $id)->pluck('modifiedBy')->unique();
        
        $html = "<h1>{$entry->title}</h1>";
        $html .= "<div>{$entry->content}</div>";
        $html .= "<p><strong>Last Modified:</strong> {$entry->lastModifiedAt} by {$entry->lastModifiedBy}</p>";
        $html .= "<p><strong>Contributors:</strong> " . implode(', ', $contributors->toArray()) . "</p>";
        $html .= "<hr><a href='/entries/{$id}/edits'>View Edit History</a> | <a href='/entries'>Back to List</a>";
        
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
            'lastModifiedBy' => $request->modifiedBy,
            'lastModifiedAt' => now(),
        ]);

        WikiEdit::create([
            'entry_id' => $entry->id,
            'content' => $request->content,
            'modifiedBy' => $request->modifiedBy,
            'summary' => $request->summary,
        ]);

        return response()->json($entry, 200);
    }

    public function history($id)
    {
        $entry = Entry::findOrFail($id);
        $edits = WikiEdit::where('entry_id', $id)->orderBy('created_at', 'desc')->get();

        $html = "<h1>Edit History: {$entry->title}</h1><ul>";
        foreach ($edits as $edit) {
            $html .= "<li>";
            $html .= "<strong>{$edit->modifiedBy}</strong> ({$edit->created_at}): ";
            $html .= "<em>{$edit->summary}</em><br>";
            $html .= "<pre style='background: #eee; padding: 5px;'>Content: {$edit->content}</pre>";
            $html .= "</li><br>";
        }
        $html .= "</ul><a href='/entries/{$id}'>Back to Entry</a>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}