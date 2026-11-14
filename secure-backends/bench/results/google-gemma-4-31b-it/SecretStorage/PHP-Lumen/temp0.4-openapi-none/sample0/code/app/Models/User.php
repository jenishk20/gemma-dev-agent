<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Auth\Authenticatable;
use Illuminate\Contracts\Auth\Authenticatable as AuthenticatableContract;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Laravel\Lumen\Auth\Authorizable;

class User extends Model implements AuthenticatableContract
{
    use Authenticatable, Authorizable, HasFactory;

    protected $fillable = [
        'username', 'email', 'password', 'token', 'secret'
    ];

    protected $hidden = [
        'password', 'token',
    ];
}