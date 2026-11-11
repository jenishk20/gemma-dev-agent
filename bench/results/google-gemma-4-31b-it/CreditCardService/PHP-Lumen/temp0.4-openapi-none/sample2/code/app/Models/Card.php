<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Card extends Model
{
    protected $fillable = ['card_number'];

    public function phones()
    {
        return $this->belongsToMany(Phone::class, 'card_phone', 'card_id', 'phone_id');
    }
}