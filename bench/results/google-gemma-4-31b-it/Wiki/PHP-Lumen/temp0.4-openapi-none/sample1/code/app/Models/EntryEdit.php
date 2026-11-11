<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class EntryEdit extends Model
{
    protected $fillable = ['entry_id', 'content', 'modified_by', 'summary'];

    public function entry()
    {
        return $this->belongsTo(Entry::class);
    }
}