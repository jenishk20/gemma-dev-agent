<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Service extends Model
{
    protected $table = 'services';
    protected $primaryKey = 'serviceId';
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = ['serviceId', 'token', 'lastNotification'];
    public $timestamps = false;

    protected $casts = [
        'lastNotification' => 'datetime',
    ];
}