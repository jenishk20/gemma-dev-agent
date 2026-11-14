<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Product extends Model
{
    protected $fillable = ['product_name'];

    public function tags()
    {
        return $this->belongsToMany(Tag::class, 'product_tag');
    }
}