<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Click extends Model
{
    protected $table = 'clicks';
    public $timestamps = false; // We only use the custom timestamp column
    protected $fillable = ['timestamp'];
}