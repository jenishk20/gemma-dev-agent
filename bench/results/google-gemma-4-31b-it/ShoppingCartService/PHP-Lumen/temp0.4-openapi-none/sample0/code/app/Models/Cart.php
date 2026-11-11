<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Cart extends Model
{
    protected $fillable = ['cart_id'];
    public $timestamps = true;

    public function items()
    {
        return $this->hasMany(CartItem::class);
    }
}