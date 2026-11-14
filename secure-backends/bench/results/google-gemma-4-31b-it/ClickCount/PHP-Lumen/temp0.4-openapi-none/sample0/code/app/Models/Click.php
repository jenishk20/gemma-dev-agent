<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Click extends Model
{
    protected $table = 'clicks';
    
    // We disable timestamps for the standard created_at/updated_at 
    // and use our own timestamp logic as per the schema
    public $timestamps = false;

    protected $fillable = ['timestamp'];

    protected $casts = [
        'timestamp' => 'datetime',
    ];
}