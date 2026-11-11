<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;

class AppServiceProvider extends ServiceProvider
{
    public function register()
    {
        //
    }

    public function boot()
    {
        // Auto-migrate database on boot for the sake of the standalone webapp requirement
        if (File::exists(database_path('migrations'))) {
            try {
                // This is a simplified way to ensure the SQLite file exists and migrations run
                // In a real production app, this would be done via CLI
                \Illuminate\Support\Facades\Artisan::call('migrate', ['--force' => true]);
            } catch (\Exception $e) {
                // Silently fail if migrations are already run or DB is locked
            }
        }
    }
}