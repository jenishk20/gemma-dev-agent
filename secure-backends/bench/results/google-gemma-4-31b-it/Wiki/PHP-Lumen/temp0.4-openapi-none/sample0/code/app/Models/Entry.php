<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Entry extends Model
{
    protected $fillable = ['title', 'content', 'last_modified_by'];

    public function edits()
    {
        return $this->hasMany(EntryEdit::class);
    }
}