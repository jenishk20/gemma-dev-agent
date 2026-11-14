<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ServiceStatus extends Model
{
    protected $fillable = [
        'serviceId', 
        'token', 
        'lastNotification'
    ];

    public $timestamps = false;
}