<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Ware extends Model
{
    protected $fillable = ['name', 'description', 'price', 'user_id'];

    public function merchant(): BelongsTo
    {
        return $this->belongsTo(User::class, 'user_id');
    }
}