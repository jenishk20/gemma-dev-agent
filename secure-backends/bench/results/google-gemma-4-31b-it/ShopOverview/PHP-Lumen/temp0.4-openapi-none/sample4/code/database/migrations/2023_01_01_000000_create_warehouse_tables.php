<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateWarehouseTables extends Migration
{
    public function up()
    {
        Schema::create('merchants', function (Blueprint $table) {
            $table->id();
            $table->string('email')->unique();
            $table->string('name');
            $table->string('password');
            $table->timestamps();
        });

        Schema::create('wares', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->text('description');
            $table->float('price');
            $table->foreignId('merchant_id')->constrained('merchants');
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('wares');
        Schema::dropIfExists('merchants');
    }
}