<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

class AppServiceProvider extends ServiceProvider
{
    public function boot()
    {
        // Auto-migrate the database on startup for the sake of this exercise
        if (DB::connection()->getDriverName() == 'sqlite') {
            try {
                // This is a simplified way to ensure the table exists in this specific environment
                Schema::create('messages', function ($table) {
                    if (!Schema::hasTable('messages')) {
                        $table->id();
                        $table->string('username');
                        $table->text('content');
                        $table->timestamps();
                    }
                });
            } catch (\Exception $e) {
                // Table might already exist
            }
        }
    }

    public function register()
    {
        //
    }
}