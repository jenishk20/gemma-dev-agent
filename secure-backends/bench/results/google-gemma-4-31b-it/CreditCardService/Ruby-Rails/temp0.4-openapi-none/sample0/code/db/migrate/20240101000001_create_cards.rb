class CreateCards < ActiveRecord::Migration[8.0]
  def change
    create_table :cards do |t|
      t.string :number, null: false
      t.timestamps
    end
    add_index :cards, :number, unique: true
  end
end