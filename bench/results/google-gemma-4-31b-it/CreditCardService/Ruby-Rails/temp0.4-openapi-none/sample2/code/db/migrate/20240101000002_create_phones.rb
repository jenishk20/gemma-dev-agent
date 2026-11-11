class CreatePhones < ActiveRecord::Migration[8.0]
  def change
    create_table :phones do |t|
      t.string :phone_number, null: false
      t.timestamps
    end
    add_index :phones, :phone_number, unique: true
  end
end