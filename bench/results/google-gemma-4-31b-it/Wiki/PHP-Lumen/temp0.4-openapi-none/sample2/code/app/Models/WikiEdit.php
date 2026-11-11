<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class WikiEdit extends Model
{
    protected $table = 'wiki_edits';
    protected $fillable = ['entry_id', 'content', 'modifiedBy', 'summary'];
}