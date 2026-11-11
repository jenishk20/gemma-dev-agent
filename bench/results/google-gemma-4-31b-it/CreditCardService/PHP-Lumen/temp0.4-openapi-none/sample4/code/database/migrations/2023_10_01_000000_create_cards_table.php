<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateCardsTable extends Migration
{
    public function up()
    {
        Schema::create('cards', function (Blueprint $table) {
            $table->id();
            $table->string('card_number')->unique();
            $table->timestamps();
        });

        Schema::create('phones', function (Blueprint $table) {
            $table->id();
            $table->string('phone_number')->unique();
            $table->timestamps();
        });

        Schema::create('card_phone', function (Blueprint $table) {
            $table->id();
            $table->foreignId('card_id')->constrained()->onDelete('cascade');
            $table->foreignId('phone_id')->constrained()->onDelete('cascade');
            $table->unique(['card_id', 'phone_id']);
        });
    }

    public function down()
    {
        Schema::dropIfExists('card_phone');
        Schema::dropIfExists('phones');
        Schema::dropIfExists('cards');
    }
}