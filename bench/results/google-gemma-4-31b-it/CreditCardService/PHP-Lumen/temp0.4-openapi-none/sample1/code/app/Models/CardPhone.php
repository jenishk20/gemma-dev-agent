<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CardPhone extends Model
{
    protected $table = 'card_phone';
    public $timestamps = false;
    protected $fillable = ['credit_card', 'phone'];
}