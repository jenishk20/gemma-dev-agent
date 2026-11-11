<?php

namespace App\Models;

use Illuminate\Auth\Authenticatable;
use Illuminate\Contracts\Auth\Authenticatable as AuthenticatableContract;
use Illuminate\Contracts\Auth\Accessibly as AccessiblesContract;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class User extends Model implements AuthenticatableContract, AccessiblesContract
{
    use Authenticatable;

    protected $fillable = ['email', 'name', 'password'];
    protected $hidden = ['password'];

    public function wares(): HasMany
    {
        return $this->hasMany(Ware::class);
    }
}