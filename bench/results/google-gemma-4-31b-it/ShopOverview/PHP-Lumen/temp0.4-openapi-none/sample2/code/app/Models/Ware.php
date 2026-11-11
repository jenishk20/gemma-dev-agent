<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Ware extends Model
{
    protected $fillable = ['merchant_id', 'name', 'description', 'price'];

    public function merchant()
    {
        return $this->belongsTo(Merchant::class);
    }
}