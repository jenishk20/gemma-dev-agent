<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

class AppServiceProvider extends ServiceProvider
{
    public function boot()
    {
        // Automatically run migrations on boot for the SQLite database
        // This ensures the db.sqlite3 file and table exist when the server starts
        if (!file_exists(database_path('migrations'))) {
            return;
        }
        
        try {
            Artisan::call('migrate', ['--force' => true]);
        } catch (\Exception $e) {
            // Log or handle migration errors
        }
    }

    public function register()
    {
        //
    }
}