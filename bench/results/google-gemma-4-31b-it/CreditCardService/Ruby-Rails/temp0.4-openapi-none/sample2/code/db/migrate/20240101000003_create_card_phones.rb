class CreateCardPhones < ActiveRecord::Migration[8.0]
  def change
    create_table :card_phones do |t|
      t.references :card, null: false, foreign_key: true
      t.references :phone, null: false, foreign_key: true
      t.timestamps
    end
    add_index :card_phones, [:card_id, :phone_id], unique: true
  end
end