class CreateServiceStatuses < ActiveRecord::Migration[8.0]
  def change
    create_table :service_statuses, id: :integer do |t|
      t.string :service_id, null: false
      t.string :token, null: false
      t.datetime :last_notification_at, null: false

      t.timestamps
    end
    add_index :service_statuses, :service_id, unique: true
    add_index :service_statuses, :token
  end
end