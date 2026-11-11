<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class User extends Model
{
    protected $fillable = [
        'username', 'email', 'password', 'secret', 'api_token',
    ];

    protected $hidden = [
        'password',
    ];
}