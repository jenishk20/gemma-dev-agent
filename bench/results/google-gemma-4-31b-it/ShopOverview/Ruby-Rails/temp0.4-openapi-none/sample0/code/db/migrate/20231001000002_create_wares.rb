class CreateWares < ActiveRecord::Migration[8.0]
  def change
    create_table :wares do |t|
      t.string :name, null: false
      t.text :description, null: false
      t.float :price, null: false
      t.references :merchant, null: false, foreign_key: true
      t.timestamps
    end
  end
end