<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CartItem extends Model
{
    protected $table = 'cart_items';
    public $timestamps = false;

    protected $fillable = ['cart_id', 'item_id', 'count'];
}