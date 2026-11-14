<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Image extends Model
{
    protected $fillable = ['filename', 'mime_type'];
    protected $keyType = 'string';
    public $incrementing = false;
}