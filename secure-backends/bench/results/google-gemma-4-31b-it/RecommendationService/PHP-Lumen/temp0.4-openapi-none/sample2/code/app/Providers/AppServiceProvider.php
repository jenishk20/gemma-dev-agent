<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\Artisan;

class AppServiceProvider extends ServiceProvider
{
    public function boot()
    {
        // Automatically run migrations on startup to ensure SQLite db is ready
        if (env('APP_ENV') === 'local') {
            Artisan::call('migrate', ['--force' => true]);
        }
    }

    public function register()
    {
        //
    }
}