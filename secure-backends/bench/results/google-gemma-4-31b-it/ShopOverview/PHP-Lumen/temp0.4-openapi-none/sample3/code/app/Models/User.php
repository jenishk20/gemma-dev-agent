<?php

namespace App\Models;

use Illuminate\Auth\Authenticatable;
use Illuminate\Contracts\Auth\Authenticatable as AuthenticatableContract;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class User extends Model implements AuthenticatableContract
{
    use Authenticatable;

    protected $fillable = ['name', 'email', 'password'];
    protected $hidden = ['password'];

    public function wares(): HasMany
    {
        return $this->hasMany(Ware::class);
    }
}