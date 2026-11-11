<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Cart extends Model
{
    protected $table = 'carts';
    public $timestamps = true;

    protected $fillable = ['cart_id'];

    public function items()
    {
        return $this->hasMany(CartItem::class, 'cart_id', 'cart_id');
    }

    protected static function boot()
    {
        parent::boot();
        static::creating(function ($model) {
            if (empty($model->cart_id)) {
                $model->cart_id = (string) Str::uuid();
            }
        });
    }
}