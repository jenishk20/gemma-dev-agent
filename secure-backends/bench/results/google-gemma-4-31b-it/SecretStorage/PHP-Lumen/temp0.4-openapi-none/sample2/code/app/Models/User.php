<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class User extends Model
{
    protected $fillable = [
        'username', 'email', 'password', 'api_token', 'secret',
    ];

    protected $hidden = [
        'password',
    ];
}