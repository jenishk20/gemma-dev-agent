<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Artisan;

class AppServiceProvider extends ServiceProvider
{
    public function register()
    {
        //
    }

    public function boot()
    {
        // Auto-run migrations on boot for the sake of the exercise 
        // to ensure db.sqlite3 is populated without manual artisan calls
        if (app()->environment('local')) {
            try {
                Artisan::call('migrate', ['--force' => true]);
            } catch (\Exception $e) {
                // Fail silently if migrations are already run or DB not ready
            }
        }
    }
}