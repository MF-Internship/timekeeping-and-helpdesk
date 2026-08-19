import styles from "./MobiFoneLogo.module.css";

export function MobiFoneLogo() {
  return (
    <picture className={styles.picture}>
      <source
        media="(min-width: 48rem)"
        srcSet="/brand/logo-desktop.png"
        width="659"
        height="400"
      />
      <img
        className={styles.logo}
        src="/brand/logo-phone.jpg"
        width="1436"
        height="1026"
        alt="MobiFone"
      />
    </picture>
  );
}
