<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Image extends Model
{
    protected $fillable = ['original_name', 'mime_type', 'path'];
    public $timestamps = true;
}