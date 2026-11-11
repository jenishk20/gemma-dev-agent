<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CardPhone extends Model
{
    protected $table = 'card_phones';
    protected $fillable = ['credit_card', 'phone'];
    public $timestamps = false;
}