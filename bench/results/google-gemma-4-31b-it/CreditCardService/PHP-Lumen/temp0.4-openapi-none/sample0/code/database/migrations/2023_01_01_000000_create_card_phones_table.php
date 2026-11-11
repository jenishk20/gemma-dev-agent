<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateCardPhonesTable extends Migration
{
    public function up()
    {
        Schema::create('card_phones', function (Blueprint $table) {
            $table->id();
            $table->string('credit_card');
            $table->string('phone');
            $table->unique(['credit_card', 'phone']);
        });
    }

    public function down()
    {
        Schema::dropIfExists('card_phones');
    }
}