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
        // Automatically run migrations on boot for the sqlite database
        if (app()->environment('local')) {
            if (!file_exists(database_path('migrations/2023_01_01_000000_create_messages_table.php'))) {
                return;
            }
            
            // This is a shortcut to ensure the DB is initialized in a container environment
            try {
                Artisan::call('migrate', ['--force' => true]);
            } catch (\Exception $e) {
                // Fail silently if migration fails during boot
            }
        }
    }
}