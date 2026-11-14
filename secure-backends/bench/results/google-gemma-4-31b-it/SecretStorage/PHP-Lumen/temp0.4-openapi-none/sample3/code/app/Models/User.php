<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Auth\Authenticatable;
use Illuminate\Contracts\Auth\Authenticatable as AuthenticatableContract;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class User extends Model implements AuthenticatableContract
{
    use HasFactory;

    protected $fillable = [
        'username', 'email', 'password', 'api_token', 'secret'
    ];

    protected $hidden = [
        'password', 'api_token',
    ];

    protected $casts = [
        'email_verified_at' => 'datetime',
    ];
}