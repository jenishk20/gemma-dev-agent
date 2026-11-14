<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

class AppServiceProvider extends ServiceProvider
{
    public function boot()
    {
        // Automatically run migrations on startup for the SQLite db
        if (app()->environment('local')) {
            try {
                // This ensures the table exists without needing a separate artisan command in simple setups
                if (!DB::getSchemaBuilder()->hasTable('users')) {
                    $this->createUsersTable();
                }
            } catch (\Exception $e) {
                // Handle cases where DB is not yet initialized
            }
        }
    }

    private function createUsersTable()
    {
        Schema::create('users', function ($table) {
            $table->id();
            $table->string('username')->unique();
            $table->text('profile_page');
            $table->binary('profile_photo');
            $table->timestamps();
        });
    }

    public function register()
    {
        //
    }
}