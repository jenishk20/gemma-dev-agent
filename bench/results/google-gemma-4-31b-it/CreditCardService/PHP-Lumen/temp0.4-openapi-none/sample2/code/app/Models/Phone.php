<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Phone extends Model
{
    protected $fillable = ['phone_number'];

    public function cards()
    {
        return $this->belongsToMany(Card::class, 'card_phone', 'phone_id', 'card_id');
    }
}